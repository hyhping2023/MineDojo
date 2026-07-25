// --------------------------------------------------------------------------------------------------
//  Copyright (c) 2016 Microsoft Corporation
//  
//  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
//  associated documentation files (the "Software"), to deal in the Software without restriction,
//  including without limitation the rights to use, copy, modify, merge, publish, distribute,
//  sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//  
//  The above copyright notice and this permission notice shall be included in all copies or
//  substantial portions of the Software.
//  
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
//  NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
//  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
//  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// --------------------------------------------------------------------------------------------------

package com.microsoft.Malmo.MissionHandlers;

import io.netty.buffer.ByteBuf;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.ContainerChest;
import net.minecraft.inventory.IInventory;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fml.common.network.ByteBufUtils;
import net.minecraftforge.fml.common.network.simpleimpl.IMessage;
import net.minecraftforge.fml.common.network.simpleimpl.IMessageHandler;
import net.minecraftforge.fml.common.network.simpleimpl.MessageContext;

import com.microsoft.Malmo.MalmoMod;
import com.microsoft.Malmo.Schemas.MissionInit;

/**
 * Chest commands allow agents to interact with chests and other container blocks.
 * Commands: "chest" to open/close chest, "chestMove <from> <to>" to move items between slots.
 */
public class ChestCommandsImplementation extends CommandBase
{
    private boolean isOverriding;

    public static class ChestMessage implements IMessage
    {
        String verb;
        String parameter;
        public ChestMessage()
        {
        }
    
        public ChestMessage(String verb, String parameter)
        {
            this.verb = verb;
            this.parameter = parameter;
        }

        @Override
        public void fromBytes(ByteBuf buf)
        {
            this.verb = ByteBufUtils.readUTF8String(buf);
            this.parameter = ByteBufUtils.readUTF8String(buf);
        }

        @Override
        public void toBytes(ByteBuf buf)
        {
            ByteBufUtils.writeUTF8String(buf, this.verb);
            ByteBufUtils.writeUTF8String(buf, this.parameter);
        }
    }

    public static class ChestMessageHandler implements IMessageHandler<ChestMessage, IMessage>
    {
        @Override
        public IMessage onMessage(final ChestMessage message, MessageContext ctx)
        {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null)
                return null;

            player.getServer().addScheduledTask(new Runnable()
            {
                @Override
                public void run()
                {
                    if (message.verb.equalsIgnoreCase("chest"))
                    {
                        if (player.openContainer instanceof ContainerChest)
                        {
                            // Close chest by closing the container
                            player.closeScreen();
                            MalmoMod.setAllowGuiInteract(false);
                        }
                        else
                        {
                            // Enable GUI interact so next right-click opens the chest
                            MalmoMod.setAllowGuiInteract(true);
                        }
                    }
                    else if (message.verb.equalsIgnoreCase("chestMove"))
                    {
                        if (player.openContainer instanceof ContainerChest)
                        {
                            ContainerChest container = (ContainerChest) player.openContainer;
                            try
                            {
                                String[] parts = message.parameter.split(" ");
                                if (parts.length >= 2)
                                {
                                    int fromSlot = Integer.parseInt(parts[0].trim());
                                    int toSlot = Integer.parseInt(parts[1].trim());
                                    if (fromSlot >= 0 && fromSlot < container.inventorySlots.size()
                                        && toSlot >= 0 && toSlot < container.inventorySlots.size())
                                    {
                                        ItemStack fromStack = container.getSlot(fromSlot).getStack();
                                        ItemStack toStack = container.getSlot(toSlot).getStack();
                                        container.getSlot(fromSlot).putStack(toStack);
                                        container.getSlot(toSlot).putStack(fromStack);
                                        container.detectAndSendChanges();
                                    }
                                    else
                                    {
                                        System.out.println("ChestCommands: slot indices out of bounds");
                                    }
                                }
                                else
                                {
                                    System.out.println("ChestCommands: malformed chestMove parameters, expected <from> <to>");
                                }
                            }
                            catch (NumberFormatException e)
                            {
                                System.out.println("ChestCommands: invalid slot index: " + message.parameter);
                            }
                        }
                        else
                        {
                            System.out.println("ChestCommands: no chest GUI open");
                        }
                    }
                }
            });
            return null;
        }
    }

    @Override
    protected boolean onExecute(String verb, String parameter, MissionInit missionInit)
    {
        if (verb.equalsIgnoreCase("chest") || verb.equalsIgnoreCase("chestMove"))
        {
            MalmoMod.network.sendToServer(new ChestMessage(verb, parameter));
            return true;
        }
        return false;
    }

    @Override
    public boolean parseParameters(Object params)
    {
        return true;
    }

    @Override
    public void install(MissionInit missionInit)
    {
    }

    @Override
    public void deinstall(MissionInit missionInit)
    {
    }

    @Override
    public boolean isOverriding()
    {
        return this.isOverriding;
    }

    @Override
    public void setOverriding(boolean b)
    {
        this.isOverriding = b;
    }
}
